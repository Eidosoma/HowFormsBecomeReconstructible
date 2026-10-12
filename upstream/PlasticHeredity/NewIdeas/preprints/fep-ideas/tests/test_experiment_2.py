from __future__ import annotations

import json

import joblib
import numpy as np
import pytest

from fep_surprise_15.observers import INVARIANT_KNN, SHELF, fit_observer_ensemble
from fep_surprise_15.validation import _scientific_geometry
from fep_surprise_2.atlas import RelabeledObserverEnsemble
from fep_surprise_2.campaign import (
    analyze,
    develop,
    generate_confirmation,
    prepare_confirmation,
    register,
    replay_confirmation,
    status,
    validate_stage,
)
from fep_surprise_2.config import profile_config
from fep_surprise_2.interventions import (
    arm_launches,
    launch_metrics,
    nested_swap_orders,
)
from plastic_heredity.config import CANDIDATES, GardConfig
from plastic_heredity.simulator import generate_beta, generate_initial_composition


def test_nested_permutations_and_exact_isomorphism_have_zero_aligned_mismatch() -> None:
    gard = GardConfig()
    rng = np.random.default_rng(2)
    beta = generate_beta(gard, rng)
    state = generate_initial_composition(gard, rng)
    orders = nested_swap_orders(gard.n_types, 22)
    changed = [np.count_nonzero(orders[count] != np.arange(gard.n_types)) for count in orders]
    assert changed == [10, 30, 60, 100]
    assert all(np.array_equal(order[order], np.arange(gard.n_types)) for order in orders.values())
    launch = arm_launches(beta, state, orders)["ISOMORPHIC_BOTH_100"]
    for candidate in ("02", "03"):
        metrics = launch_metrics(beta, state, launch, gard, CANDIDATES[candidate])
        assert metrics[-1] <= 1e-12


def test_relabeling_view_is_exact_for_both_primary_observers() -> None:
    parents, phases, lineages = _scientific_geometry(3)
    model = fit_observer_ensemble(
        parents[:400],
        phases[:400],
        lineages[:400],
        pseudocount=0.5,
        reference_mass=80.0,
        pca_variance=0.95,
        pca_min=2,
        pca_max=6,
        knn_k=5,
        mixture_k_max=2,
        training_subsample=80,
        seed=2,
    )
    order = nested_swap_orders(100, 3)[100]
    relabeled = RelabeledObserverEnsemble(model, order)
    assert joblib.hash(model) == joblib.hash(relabeled.native)
    for observer in (INVARIANT_KNN, SHELF):
        assert np.allclose(
            model.anomaly_grid(phases[:16], observer),
            relabeled.anomaly_grid(phases[:16, :, order], observer),
            atol=1e-12,
            rtol=0.0,
        )


def test_complete_experiment_2_smoke_campaign_enforces_two_firewalls(tmp_path) -> None:
    config = profile_config("smoke")
    validate_stage(tmp_path, config)
    register(tmp_path, config)
    develop(tmp_path, config, workers=2)
    confirmation = prepare_confirmation(tmp_path, config, workers=2)
    assert (confirmation / "confirmation_design.json").is_file()
    assert not list((confirmation / "cells").glob("*_futures.joblib"))
    generate_confirmation(tmp_path, config, workers=2)
    assert not (confirmation / "metrics.json").exists()
    assert not (confirmation / "REPORT.md").exists()
    with pytest.raises(FileNotFoundError):
        analyze(tmp_path, config)
    replay = replay_confirmation(tmp_path, config, workers=2)
    replay_payload = json.loads((replay / "replay.json").read_text())
    assert replay_payload["all_exact"] is True
    result = analyze(tmp_path, config)
    metrics = json.loads((result / "metrics.json").read_text())
    assert metrics["decision"]["integrity_verdict"] == "VALID"
    assert metrics["decision"]["scientific_verdict"] == "NONSCIENTIFIC_PROFILE"
    assert metrics["decision"]["profile_is_scientifically_eligible"] is False
    state = status(tmp_path, "smoke")
    assert all(
        state[name]["sealed"]
        for name in (
            "validation",
            "registration",
            "development",
            "confirmation",
            "confirmation_replay",
            "analysis",
        )
    )
