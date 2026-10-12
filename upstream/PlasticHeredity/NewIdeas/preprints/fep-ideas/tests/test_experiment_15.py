from __future__ import annotations

import json

import joblib
import numpy as np
import pytest

from fep_surprise_15.analysis import _matched_foreign_indices
from fep_surprise_15.campaign import (
    analyze,
    develop,
    generate_confirmation,
    register,
    replay_confirmation,
    status,
    validate_stage,
)
from fep_surprise_15.config import profile_config
from fep_surprise_15.observers import (
    INVARIANT_KNN,
    LEGACY_KNN,
    SHELF,
    fit_observer_ensemble,
    invariant_clr,
    legacy_clr,
    scale_invariance_error,
)
from fep_surprise_15.predictor import select_and_fit
from fep_surprise_15.validation import _scientific_geometry


def _small_ensemble():
    parents, phases, lineages = _scientific_geometry(3)
    return fit_observer_ensemble(
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
        seed=15,
    ), parents[:16]


def test_invariant_clr_matches_parent_geometry_and_removes_mass_scale() -> None:
    ensemble, parents = _small_ensemble()
    assert np.allclose(legacy_clr(parents), invariant_clr(parents), atol=1e-12)
    assert scale_invariance_error(ensemble, parents, INVARIANT_KNN) <= 1e-10
    assert scale_invariance_error(ensemble, parents, SHELF) <= 1e-10
    assert scale_invariance_error(ensemble, parents, LEGACY_KNN) > 1e-6


def test_observer_fit_and_scores_are_exactly_repeatable() -> None:
    first, parents = _small_ensemble()
    second, _ = _small_ensemble()
    assert joblib.hash(first) == joblib.hash(second)
    for observer in (LEGACY_KNN, INVARIANT_KNN, SHELF):
        assert np.array_equal(first.raw(parents, observer), second.raw(parents, observer))


def test_foreign_matching_is_a_deterministic_derangement() -> None:
    descriptors = np.arange(25, dtype=float).reshape(5, 5)
    first = _matched_foreign_indices(descriptors)
    second = _matched_foreign_indices(descriptors)
    assert np.array_equal(first, second)
    assert sorted(first.tolist()) == list(range(5))
    assert np.all(first != np.arange(5))


def test_platt_calibration_never_reverses_development_ranking() -> None:
    values = np.arange(80, dtype=float).reshape(40, 2)
    labels = np.asarray([0, 1] * 20, dtype=np.int8)
    matrices = np.repeat(np.arange(8), 5)
    model = select_and_fit(values, labels, matrices, (0.1, 1.0), 4)
    assert model.calibration_slope >= 0.0


def test_complete_experiment_15_smoke_campaign_enforces_replay_firewall(
    tmp_path,
) -> None:
    config = profile_config("smoke")
    validate_stage(tmp_path, config)
    register(tmp_path, config)
    develop(tmp_path, config, workers=2)
    confirmation = generate_confirmation(tmp_path, config, workers=2)
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
