import numpy as np
import pytest

import two_mode as tm


def test_response_formula_matches_hidden_chain_distribution():
    for params in ([.8, .25, .99, 1., 1.], [.8, .25, .92, .25, 1.], [.3, .6, .7, .6, -.5]):
        initial, matrix = tm.hidden_model(params)
        for h in [0, 1, 2, 8, 32, 64]:
            explicit = initial @ np.linalg.matrix_power(matrix, h) @ tm.EMISSION
            assert tm.distributions(params, [h])[0] == pytest.approx(explicit, abs=1e-13)


def test_short_pattern_probabilities_and_marginals_are_consistent():
    params = [.8, .25, .99, .25, 1.]
    probabilities = tm.pattern_probabilities(params)
    assert probabilities.sum() == pytest.approx(1.)
    for t in (0, 1, 2):
        marginal = np.bincount(tm.PATTERNS[:, t], weights=probabilities, minlength=3)
        assert marginal == pytest.approx(tm.distributions(params, [t])[0])


def test_exact_observable_identification_recovers_nonstationary_parameters():
    for params in ([.8, .25, .99, 1., 1.], [.8, .25, .92, .25, 1.], [.3, .6, .7, .6, -.5]):
        assert tm.exact_moment_identification(tm.distributions(params, [0, 1, 2])) == pytest.approx(params, abs=1e-12)


def test_unidentifiable_and_inconsistent_moments_are_rejected():
    stationary = tm.distributions([.8, .25, .99, .8, 1.], [0, 1, 2])
    with pytest.raises(ValueError, match="unidentifiable"):
        tm.exact_moment_identification(stationary)
    inconsistent = tm.distributions([.8, .25, .99, 1., 1.], [0, 1, 2])
    inconsistent[2, 0] -= .02
    inconsistent[2, 1] += .02
    with pytest.raises(ValueError, match="contradicts"):
        tm.exact_moment_identification(inconsistent)


def test_fit_returns_normalized_observable_forecasts():
    # Deterministic rounded expected counts, solely an estimator sanity check.
    counts = np.rint(10000*tm.pattern_probabilities([.8, .25, .98, .5, .9])).astype(int)
    fitted = tm.fit_patterns(counts)
    probabilities = tm.distributions(fitted["params"], [0, 1, 2, 32])
    assert (probabilities >= -1e-12).all()
    assert probabilities.sum(axis=1) == pytest.approx(np.ones(4))
    assert fitted["average_negative_log_likelihood"] >= 0
