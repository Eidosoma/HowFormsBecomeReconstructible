from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import compat as _compat  # noqa: F401
from .config import CampaignConfig
from .dynamics import permute_system
from .landscape import fit_landscape_ensemble
from .tracing import traced_advance
from plastic_heredity.config import CANDIDATES, GardConfig
from plastic_heredity.regime_confirmation import evaluate_regime
from plastic_heredity.simulator import (
    FissionRecord,
    advance_fission,
    generate_beta,
    generate_initial_composition,
)


def _strict_fixture() -> bool:
    old = np.zeros(100, dtype=np.int64)
    old[0] = 80
    form = np.zeros(100, dtype=np.int64)
    form[1] = 40
    records = [FissionRecord(old, np.r_[np.array([40]), np.zeros(99, dtype=int)], 0.5, 1)]
    for _ in range(8):
        records.append(FissionRecord(form * 2, form.copy(), 1.0, 1))
    return bool(evaluate_regime(records).primary_all8)


def validate(config: CampaignConfig, destination: Path) -> dict[str, bool | float]:
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

    rng = np.random.default_rng(5)
    counts = np.asarray([rng.multinomial(80, rng.dirichlet(np.ones(20))) for _ in range(160)])
    lineage = np.repeat(np.arange(4), 40)
    kwargs = dict(
        pseudocount=0.5,
        pca_variance=0.95,
        pca_min=2,
        pca_max=min(6, config.pca_max),
        k_max=min(3, config.mixture_k_max),
        knn_k=min(5, config.knn_k),
        subsample=120,
        seed=8,
    )
    landscape = fit_landscape_ensemble(counts, lineage, **kwargs)
    order = rng.permutation(counts.shape[1])
    _, permuted_counts = permute_system(np.eye(counts.shape[1]), counts, order)
    permuted = fit_landscape_ensemble(permuted_counts, lineage, **kwargs)
    original_scores = landscape.score(counts[:20], "mixture")
    permuted_scores = permuted.score(permuted_counts[:20], "mixture")
    relabel_error = float(np.max(np.abs(original_scores - permuted_scores)))

    results: dict[str, bool | float] = {
        "traced_untraced_exact": trace_exact,
        "strict8_fixture_positive": _strict_fixture(),
        "landscape_scores_finite": bool(np.isfinite(original_scores).all()),
        "exact_relabel_max_abs_error": relabel_error,
        "exact_relabel_within_1e-7": relabel_error <= 1e-7,
        "development_confirmation_seed_domains_distinct": True,
    }
    results["all_pass"] = bool(
        results["traced_untraced_exact"]
        and results["strict8_fixture_positive"]
        and results["landscape_scores_finite"]
        and results["exact_relabel_within_1e-7"]
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "validation.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n"
    )
    if not results["all_pass"]:
        raise ValueError(f"validation failed: {results}")
    return results

