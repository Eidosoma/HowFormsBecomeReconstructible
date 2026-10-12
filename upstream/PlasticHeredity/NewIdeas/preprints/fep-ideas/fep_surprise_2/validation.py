from __future__ import annotations

import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from fep_surprise_15 import compat as _compat  # noqa: F401
from fep_surprise_15.observers import INVARIANT_KNN, SHELF, fit_observer_ensemble
from fep_surprise_15.validation import _scientific_geometry
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

from .atlas import RelabeledObserverEnsemble
from .config import Campaign2Config
from .interventions import (
    arm_launches,
    beta_variants,
    launch_metrics,
    log_morph,
    nested_swap_orders,
)


VALIDATION_SEED = 0x2A11D


def _observer_kwargs(config: Campaign2Config) -> dict[str, Any]:
    return {
        "pseudocount": config.pseudocount,
        "reference_mass": config.reference_mass,
        "pca_variance": config.pca_variance,
        "pca_min": config.pca_min,
        "pca_max": 20,
        "knn_k": config.knn_k,
        "mixture_k_max": min(config.mixture_k_max, 3),
        "training_subsample": 800,
        "seed": VALIDATION_SEED,
    }


def _fresh_process_fit(config: Campaign2Config) -> dict[str, Any]:
    parents, phases, lineages = _scientific_geometry(len(config.phase_grid))
    model = fit_observer_ensemble(
        parents, phases, lineages, **_observer_kwargs(config)
    )
    probe = phases[:32]
    return {
        "model_hash": joblib.hash(model),
        "scores": {
            observer: model.anomaly_grid(probe, observer)
            for observer in (INVARIANT_KNN, SHELF)
        },
    }


def _strict_fixture(order: np.ndarray | None = None) -> bool:
    old = np.zeros(100, dtype=np.int64)
    old[0] = 80
    form = np.zeros(100, dtype=np.int64)
    form[1] = 40
    records = [FissionRecord(old, old // 2, 0.5, 1)]
    records.extend(FissionRecord(form * 2, form.copy(), 1.0, 1) for _ in range(8))
    if order is not None:
        records = [
            FissionRecord(
                item.parent[order], item.daughter[order], item.h, item.growth_steps
            )
            for item in records
        ]
    return bool(evaluate_regime(records).primary_all8)


def validate(config: Campaign2Config, destination: Path) -> dict[str, Any]:
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
    repeat_errors = {
        observer: float(
            np.max(
                np.abs(
                    first.anomaly_grid(probe, observer)
                    - second.anomaly_grid(probe, observer)
                )
            )
        )
        for observer in (INVARIANT_KNN, SHELF)
    }
    repeated_hash = joblib.hash(first) == joblib.hash(second)
    spawn = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=spawn) as executor:
        one_worker = executor.submit(_fresh_process_fit, config).result()
    with ProcessPoolExecutor(max_workers=2, mp_context=spawn) as executor:
        two_workers = [
            future.result()
            for future in (
                executor.submit(_fresh_process_fit, config),
                executor.submit(_fresh_process_fit, config),
            )
        ]
    process_results = [one_worker, *two_workers]
    fresh_process_hash_exact = all(
        item["model_hash"] == joblib.hash(first) for item in process_results
    )
    fresh_process_errors = {
        observer: max(
            float(
                np.max(
                    np.abs(
                        item["scores"][observer]
                        - first.anomaly_grid(probe, observer)
                    )
                )
            )
            for item in process_results
        )
        for observer in (INVARIANT_KNN, SHELF)
    }

    orders = nested_swap_orders(100, VALIDATION_SEED + 1)
    full = orders[100]
    relabeled = RelabeledObserverEnsemble(first, full)
    relabel_errors = {
        observer: float(
            np.max(
                np.abs(
                    first.anomaly_grid(probe, observer)
                    - relabeled.anomaly_grid(probe[..., full], observer)
                )
            )
        )
        for observer in (INVARIANT_KNN, SHELF)
    }
    variants = beta_variants(beta, orders)
    launches = arm_launches(beta, initial, orders)
    isomorphic_metrics = {
        candidate: launch_metrics(
            beta,
            initial,
            launches["ISOMORPHIC_BOTH_100"],
            gard,
            CANDIDATES[candidate],
        )
        for candidate in ("02", "03")
    }
    aligned_errors = {
        candidate: float(abs(values[-1]))
        for candidate, values in isomorphic_metrics.items()
    }
    morph_zero = log_morph(beta, variants["perm_100"], 0.0)
    morph_one = log_morph(beta, variants["perm_100"], 1.0)
    morph_endpoint_errors = {
        "zero": float(np.max(np.abs(morph_zero / beta - 1.0))),
        "one": float(
            np.max(
                np.abs(
                    morph_one / variants["perm_100"] - 1.0
                )
            )
        ),
    }
    nesting = all(
        np.count_nonzero(orders[count] != np.arange(100)) == count
        and np.array_equal(orders[count][orders[count]], np.arange(100))
        for count in config.permutation_counts
    )
    seed_firewall = bool(
        derive_seed(config.master_seed, "development.beta", 0)
        != derive_seed(config.master_seed, "confirmation.beta", 0)
        and derive_seed(config.master_seed, "development.future.common", 0)
        != derive_seed(config.master_seed, "confirmation.future.common", 0)
    )
    results: dict[str, Any] = {
        "format": "fep-surprise-2-validation-v1",
        "traced_untraced_exact": trace_exact,
        "strict8_fixture_positive": _strict_fixture(),
        "strict8_relabel_invariant": _strict_fixture(full),
        "scientific_scale_shape": [800, 100],
        "repeated_model_hash_exact": repeated_hash,
        "repeated_score_max_abs_errors": repeat_errors,
        "fresh_process_worker_count_model_hash_exact": fresh_process_hash_exact,
        "fresh_process_worker_count_score_max_abs_errors": fresh_process_errors,
        "relabel_max_abs_errors": relabel_errors,
        "nested_swap_counts_exact": nesting,
        "isomorphism_aligned_local_mismatch": aligned_errors,
        "morph_endpoint_max_abs_errors": morph_endpoint_errors,
        "development_confirmation_seed_domains_distinct": seed_firewall,
        "simulator_root": str(_compat.PLASTIC_HEREDITY_ROOT),
    }
    results["all_pass"] = bool(
        results["traced_untraced_exact"]
        and results["strict8_fixture_positive"]
        and results["strict8_relabel_invariant"]
        and results["repeated_model_hash_exact"]
        and max(repeat_errors.values()) <= 1e-12
        and results["fresh_process_worker_count_model_hash_exact"]
        and max(fresh_process_errors.values()) <= 1e-12
        and max(relabel_errors.values()) <= config.relabel_tolerance
        and results["nested_swap_counts_exact"]
        and max(aligned_errors.values()) <= config.aligned_mismatch_tolerance
        and max(morph_endpoint_errors.values()) <= 1e-12
        and results["development_confirmation_seed_domains_distinct"]
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "validation.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not results["all_pass"]:
        raise ValueError(f"Experiment 2 validation failed: {results}")
    return results
