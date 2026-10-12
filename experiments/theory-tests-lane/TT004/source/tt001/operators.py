"""Small exact finite-process checks of the RDT observation bookkeeping."""
import numpy as np


def probabilities(initial, transition, pass_transition, readout, horizon):
    mu, k, passed, q = map(lambda a: np.asarray(a, float),
                         (initial, transition, pass_transition, readout))
    n = len(mu)
    if k.shape != (n, n) or passed.shape != k.shape or q.shape != (n,):
        raise ValueError('Shape mismatch')
    if not all(np.isfinite(a).all() for a in (mu, k, passed, q)):
        raise ValueError('Nonfinite process')
    if min(mu.min(), k.min(), passed.min(), q.min()) < 0 or q.max() > 1:
        raise ValueError('Invalid probabilities')
    if not np.allclose(k.sum(axis=1), 1.) or not np.isclose(mu.sum(), 1.):
        raise ValueError('Not stochastic')
    if (passed > k+1e-14).any() or not isinstance(horizon, int) or horizon < 0:
        raise ValueError('Invalid pass kernel or horizon')
    return float(mu@np.linalg.matrix_power(k, horizon)@q), float(
        mu@np.linalg.matrix_power(passed, horizon)@q)


def short_probe_counterexample(prefix=3, horizon=32):
    if not 0 <= prefix < horizon:
        raise ValueError('Need a longer future than observed prefix')
    n = prefix+2
    a, b = np.zeros((n, n)), np.zeros((n, n))
    for i in range(n):
        a[i, min(i+1, prefix) if i <= prefix else i] = 1.
        b[i, min(i+1, n-1)] = 1.
    mu = np.eye(n)[0]
    q = np.ones(n); q[-1] = 0.
    first = [float(mu@np.linalg.matrix_power(a, t)@q) for t in range(prefix+1)]
    second = [float(mu@np.linalg.matrix_power(b, t)@q) for t in range(prefix+1)]
    return dict(prefix_observations_a=first, prefix_observations_b=second,
        terminal_a=float(mu@np.linalg.matrix_power(a, horizon)@q),
        terminal_b=float(mu@np.linalg.matrix_power(b, horizon)@q),
        interpretation='Identical short observations do not identify unrestricted later dynamics.')
