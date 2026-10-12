from __future__ import annotations

import numpy as np

from fep_surprise.landscape import (
    clr_transform,
    fit_fixed_target_landscape,
    fit_landscape_ensemble,
    fit_phase_conditional_ensemble,
)


def _synthetic_reference(seed: int = 1) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    states = []
    lineages = []
    for lineage in range(4):
        for draw in range(40):
            p = np.full(12, 0.01)
            if draw % 2:
                p[6:9] += 0.29
            else:
                p[:3] += 0.29
            p /= p.sum()
            states.append(rng.multinomial(80, p))
            lineages.append(lineage)
    return np.asarray(states), np.asarray(lineages)


def test_clr_is_permutation_equivariant() -> None:
    states, _ = _synthetic_reference()
    order = np.array([4, 0, 2, 1, 3, 5, 11, 10, 9, 8, 7, 6])
    assert np.allclose(clr_transform(states[:, order]), clr_transform(states)[:, order])


def test_landscape_scores_are_finite_and_shelf_mixture_beats_fixed_target() -> None:
    states, lineage = _synthetic_reference()
    model = fit_landscape_ensemble(
        states,
        lineage,
        pseudocount=0.5,
        pca_variance=0.95,
        pca_min=2,
        pca_max=6,
        k_max=3,
        knn_k=5,
        subsample=120,
        seed=4,
    )
    mixture = model.score(states[:10], "mixture")
    knn = model.score(states[:10], "knn")
    assert np.isfinite(mixture).all()
    assert np.isfinite(knn).all()
    assert max(half.selected_k for half in model.halves) >= 2
    fixed = fit_fixed_target_landscape(model)
    assert all(half.selected_k == 1 for half in fixed.halves)


def test_surprise_increases_for_far_state() -> None:
    states, lineage = _synthetic_reference()
    model = fit_landscape_ensemble(
        states,
        lineage,
        pseudocount=0.5,
        pca_variance=0.95,
        pca_min=2,
        pca_max=6,
        k_max=3,
        knn_k=5,
        subsample=120,
        seed=5,
    )
    far = np.zeros((1, 12), dtype=int)
    far[0, 10:] = 40
    near = states[:20]
    assert model.score(far, "mixture")[0] > np.median(model.score(near, "mixture"))


def test_phase_conditioned_calibration_is_finite() -> None:
    states, lineage = _synthetic_reference()
    model = fit_landscape_ensemble(
        states,
        lineage,
        pseudocount=0.5,
        pca_variance=0.95,
        pca_min=2,
        pca_max=6,
        k_max=3,
        knn_k=5,
        subsample=120,
        seed=6,
    )
    phases = np.stack([states, np.maximum(states - 1, 0), states], axis=1)
    conditional = fit_phase_conditional_ensemble(phases, lineage, model)
    assert np.isfinite(conditional.score(phases[:10])).all()
