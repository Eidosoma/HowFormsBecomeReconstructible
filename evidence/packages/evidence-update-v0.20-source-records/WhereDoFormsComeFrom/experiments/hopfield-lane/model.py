"""Small Hopfield reconstruction models; no imports from other research lanes."""
from __future__ import annotations

import hashlib
import json
import numpy as np


def rng(seed, *labels):
    key = json.dumps([int(seed), *labels], separators=(",", ":")).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16], "little"))


def symmetric(x):
    w = (x + np.swapaxes(x, -1, -2)) / 2
    i = np.arange(w.shape[-1])
    w[..., i, i] = 0
    return w


def write_body(states):
    """Only present activity is available. Shape (..., observations, neurons)."""
    x = np.asarray(states, dtype=np.float64)
    w = np.einsum("...ti,...tj->...ij", x, x) / (x.shape[-2] * x.shape[-1])
    i = np.arange(x.shape[-1])
    w[..., i, i] = 0
    return w


def energy(state, weights, field=0.):
    return -.5 * np.einsum("...i,...ij,...j->...", state, weights, state) - np.sum(field * state, axis=-1)


def relax(weights, birth, orders, clamp_indices=(), clamp_values=1.):
    """Sequential binary updates; a zero local field retains the previous bit.

    Weights may broadcast across observations. Orders are externally supplied
    permutations, so different interventions consume exactly the same tape.
    """
    x = np.array(birth, dtype=np.float64, copy=True)
    fixed = np.zeros(x.shape[-1], dtype=bool)
    fixed[np.asarray(clamp_indices, dtype=int)] = True
    x[..., fixed] = clamp_values
    for order in orders:
        for i in order:
            if fixed[i]:
                continue
            local = np.einsum("...j,...j->...", weights[..., i, :], x)
            x[..., i] = np.where(local > 0, 1., np.where(local < 0, -1., x[..., i]))
    return x


def mask_edges(random, shape, probability):
    """Independent undirected edge erasures, with no gain compensation."""
    upper = np.triu(random.random(shape) >= probability, k=1)
    return upper | np.swapaxes(upper, -1, -2)


def permute_record(weights, permutation):
    return weights[..., permutation, :][..., :, permutation].copy()


def corrupted_record(weights, random, correlation=.3):
    """Exactly norm-matched, orthogonal symmetric corruption (zero diagonal)."""
    z = symmetric(random.normal(size=weights.shape))
    axes = (-2, -1)
    norm2 = np.sum(weights**2, axis=axes, keepdims=True)
    z -= weights * (np.sum(z * weights, axis=axes, keepdims=True) / norm2)
    z *= np.sqrt(norm2 / np.sum(z**2, axis=axes, keepdims=True))
    return correlation * weights + np.sqrt(1-correlation**2) * z


def graded_flow(initial, weights, duration, dt, field=0., beta=2., trace=False):
    """Graded Hopfield ODE du/dt = -u + W tanh(beta u) + I, RK4.

    Symmetric self-couplings are allowed here. Clamps, parameter changes and
    replacement boundaries are external interventions, not autonomous flow.
    """
    steps = int(round(duration / dt))
    if steps < 1 or abs(steps * dt - duration) > 1e-10:
        raise ValueError("duration must be a positive integer multiple of dt")
    u = np.array(initial, dtype=np.float64, copy=True)
    history = [u.copy()] if trace else None

    def drift(v):
        return -v + np.einsum("...ij,...j->...i", weights, np.tanh(beta * v)) + field

    for _ in range(steps):
        k1 = drift(u)
        k2 = drift(u + dt*k1/2)
        k3 = drift(u + dt*k2/2)
        k4 = drift(u + dt*k3)
        u += dt*(k1 + 2*k2 + 2*k3 + k4)/6
        if trace:
            history.append(u.copy())
    return np.stack(history) if trace else u


def graded_energy(u, weights, beta=2.):
    x = np.tanh(beta*u)
    # Integral_0^x atanh(v)/beta dv, in a stable u-based form.
    integral = u*x - (np.logaddexp(beta*u, -beta*u) - np.log(2.))/beta
    return -.5*np.einsum("...i,...ij,...j->...", x, weights, x) + integral.sum(axis=-1)
