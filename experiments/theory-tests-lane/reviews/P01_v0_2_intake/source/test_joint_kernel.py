"""Independent small-case checks for scientific accounting and error bounds."""
import itertools
import math

import numpy as np
import pytest

import joint_kernel as jk
from develop import counterexamples


def enumerate_paths(p, q, start, horizon):
    result = 0.
    for path in itertools.product(range(len(p)), repeat=horizon):
        prob, state = 1., start
        for successor in path:
            prob *= p[state, successor]
            state = successor
        result += prob*q[state]
    return result


def enumerate_joint(joint, start, horizon, q):
    result = 0.
    outcomes = list(itertools.product((0, 1), range(len(joint))))
    for path in itertools.product(outcomes, repeat=horizon):
        prob, state = 1., start
        for passed, successor in path:
            prob *= joint[state, passed, successor] * passed
            state = successor
        result += prob*q[state]
    return result


def test_expectations_against_full_path_enumeration():
    p = np.array([[.7, .3], [.2, .8]])
    q = np.array([.9, .1])
    for h in range(6):
        for i in range(2):
            assert jk.terminal(p, q, h)[i] == pytest.approx(enumerate_paths(p, q, i, h), abs=1e-12)


def test_joint_success_and_additional_terminal_assay():
    joint = np.array([[[.3, .2], [.1, .4]], [[.2, .1], [.6, .1]]])
    _, a = jk.joint_operators(joint)
    for h in range(5):
        for q in (np.ones(2), np.array([.8, .2])):
            for i in range(2):
                assert jk.all_cycle(a, h, q)[i] == pytest.approx(enumerate_joint(joint, i, h, q), abs=1e-12)


def test_failure_mass_is_preserved():
    a = np.array([[.1, .2], [.3, .2]])
    completed = jk.failure_completion(a)
    for h in range(6):
        assert jk.terminal(completed, [1, 1, 0], h)[:2] == pytest.approx(jk.all_cycle(a, h))
    assert jk.all_cycle(a, 2)[0] != pytest.approx(1.)


def test_intervention_order_has_correct_convention():
    u = np.array([[0., 1.], [0., 1.]])
    v = np.array([[0., 1.], [1., 0.]])
    assert jk.ordered_terminal([u, v], [1, 0])[0] == 1.
    assert jk.ordered_terminal([v, u], [1, 0])[0] == 0.


def test_closed_form_for_both_identities_and_readiness_states():
    for p, a, r in ((.005, .15, .6), (.04, .15, .6), (0., 0., 0.), (.8, .9, .9)):
        matrix = jk.two_factor_kernel(p, a, r)
        for h in (0, 1, 2, 8, 32, 64):
            actual = jk.terminal(matrix, [0, 1, 0, 0], h)
            expected = [jk.two_factor_exact(p, a, r, h, own=i//2 == 0, ready=bool(i % 2)) for i in range(4)]
            assert actual == pytest.approx(expected, abs=2e-14)


def test_aggregation_and_bound_on_random_finite_chains():
    rng = np.random.default_rng(777)
    for _ in range(25):
        p = rng.dirichlet(np.ones(6), size=6)
        q = rng.random(6)
        info = jk.aggregate(p, q, np.array([0, 0, 1, 1, 2, 2]))
        for h in (0, 1, 2, 5, 16):
            actual = jk.terminal(p, q, h)
            predicted = info["membership"] @ jk.terminal(info["p"], info["q"], h)
            bound = jk.terminal_error_bound(info["p"], info["q"], h, info["transition_defect"], info["readout_defect"])
            assert np.max(np.abs(actual-predicted)) <= bound+1e-12


def test_exact_lumping_with_hidden_neutral_microstates():
    macro = np.array([[.9, .1], [.2, .8]])
    p = np.kron(macro, np.array([[.2, .8], [.7, .3]]))
    info = jk.aggregate(p, [1, 1, 0, 0], np.array([0, 0, 1, 1]))
    assert info["transition_defect"] < 1e-15
    assert info["readout_defect"] == 0
    assert info["p"] == pytest.approx(macro)


def test_binomial_sampling_radius_has_exact_finite_coverage():
    # Enumerate every possible count, rather than Monte Carlo coverage testing.
    for n in (5, 20, 60):
        radius = jk.tv_row_radius(n, 1, 2, .05)
        for p in (.02, .2, .5, .8, .98):
            outside = sum(math.comb(n, k)*p**k*(1-p)**(n-k)
                          for k in range(n+1) if abs(k/n-p) > radius)
            assert outside <= .05 + 1e-12


def test_horizon_zero_and_missing_source_support():
    assert jk.terminal(np.eye(2), [.3, .7], 0) == pytest.approx([.3, .7])
    assert jk.all_cycle(np.zeros((2, 2)), 0) == pytest.approx([1., 1.])
    with pytest.raises(ValueError, match="Unobserved"):
        jk.fit_joint(np.zeros((2, 2, 2), dtype=int))
    assert jk.tv_row_radius(0, 2, 4, .05) == 1.


@pytest.mark.parametrize("bad", [np.array([[1.1, -.1], [0, 1]]), np.array([[.5, .2], [.5, .5]]), np.array([[float('nan')]])])
def test_invalid_markov_inputs_are_rejected(bad):
    with pytest.raises(ValueError):
        jk.kernel(bad)


def test_counterexamples_reject_marginal_factorization_and_universal_identifiability():
    by_id = {c["id"]: c for c in counterexamples()}
    assert by_id["CE10"]["true_all_cycle"] == 0
    assert by_id["CE10"]["marginal_factorization"] == .125
    assert by_id["CE11"]["short_endpoint_good"] == by_id["CE11"]["short_endpoint_bad"]
    assert by_id["CE11"]["later_good"] == 1 and by_id["CE11"]["later_bad"] == 0
    assert by_id["CE09"]["readout_defect"] == 0
    assert by_id["CE09"]["transition_defect"] > 0
