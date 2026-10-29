"""A task-gated, three-property empirical reduction, not a stability theorem."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'reference'))
import lineage_dynamics as native
import writer_audit as diagnostic

DESIGN = json.loads((ROOT / 'design.json').read_text())
PORTS = native.PORTS


def rng(key, probe, channel):
    parts = [DESIGN['forcing']['namespace'], *key, probe, channel]
    payload = json.dumps(parts, separators=(',', ':')).encode()
    seed = int.from_bytes(hashlib.sha256(payload).digest()[:16], 'little')
    return np.random.Generator(np.random.PCG64(seed))


def environment(key, probe, regime):
    """The same draws are consumed in both regimes; branches share forcing."""
    cfg = DESIGN['reader']
    available = np.flatnonzero(~PORTS.any(axis=0).ravel())
    mask = np.zeros((16, 16), bool)
    mask.ravel()[rng(key, probe, 'injury').choice(available, 24, replace=False)] = True
    draws = rng(key, probe, 'forcing').standard_normal((cfg['read_steps'] + 1, 2, 16, 16))
    if regime == 'matched':
        draws[:, 1] = draws[:, 0]
    elif regime != 'independent':
        raise ValueError(regime)
    return mask, cfg['birth_sd'] * draws[0], draws[1:]


def input_branches(weights, key, probe):
    epsilon = DESIGN['features']['perturbation_fraction']
    signs = rng(key, probe, 'direction').choice([-1., 1.], size=(2, 16, 16))
    return np.stack([weights, weights * (1 + epsilon * signs), weights * (1 - epsilon * signs)])


def read_write(weights, mask, birth, noise):
    """Archived roll-based native equations; write once from the final body."""
    cfg = DESIGN['reader']
    available = native.available_edges(mask)
    effective = weights * available
    denominator = native.incident(abs(effective))
    body = np.repeat(birth[None], len(weights), axis=0)
    body *= ~mask
    body[..., PORTS[0]] = np.array([1., -1.])[None, :, None]
    windows = []
    for t, forcing in enumerate(noise):
        body = native.step(body, effective[:, None], denominator[:, None], forcing,
                           cfg, t >= cfg['settling_steps'])
        body *= ~mask
        body[..., PORTS[0]] = np.array([1., -1.])[None, :, None]
        if t >= cfg['read_steps'] - cfg['observe_steps']:
            windows.append(native.read_ports(body))
    pair, _ = native.writer_components(body[:, None, None], mask[None, None],
                                       DESIGN['writer']['beta'], 1e-4)
    return dict(end=body, windows=np.stack(windows), outgoing=pair['exact_rewrite'][:, 0, 0])


def operator(weights):
    """Four entries per incoming row; equivalent to a 256 x 256 sparse matrix."""
    return diagnostic.normalized(np.asarray(weights, float))


def distance_squared(a, b):
    return np.sum((a - b)**2, axis=(-3, -2, -1)) / 256.


def transfer(weights, rule):
    rows = operator(weights)
    signed_field = diagnostic.cue_transfer(rows, PORTS[0], 64)
    unsigned_field = diagnostic.cue_transfer(abs(rows), PORTS[0], 64)
    signed = np.minimum(rule * signed_field[..., PORTS[1]].mean(axis=-1),
                        -rule * signed_field[..., PORTS[2]].mean(axis=-1))
    unsigned = np.minimum(unsigned_field[..., PORTS[1]].mean(axis=-1),
                          unsigned_field[..., PORTS[2]].mean(axis=-1))
    return signed, unsigned


def reduce_probes(incoming, outgoing, rule):
    if incoming.shape != (4, 3, 2, 16, 16) or outgoing.shape != incoming.shape:
        raise ValueError('Exactly four baseline/plus/minus cycle probes required')
    ai, ao = operator(incoming), operator(outgoing)
    denominator = distance_squared(ai[:, 1:], ai[:, :1]).sum(axis=1)
    numerator = distance_squared(ao[:, 1:], ao[:, :1]).sum(axis=1)
    identifiable = bool(denominator.sum() > 0)
    if not identifiable and numerator.sum() > 1e-24:
        raise ArithmeticError('Identical normalized inputs produced different outputs')
    gain = float(np.sqrt(numerator.sum() / denominator.sum())) if identifiable else 1.
    signed, unsigned = transfer(outgoing, rule)
    margin = float(signed[:, 0].mean())
    spread = float(np.sqrt(distance_squared(ao[:, 0], ao[:, 0].mean(axis=0)).mean()))
    restoration = max(margin, 0.) / (1 + gain)
    features = np.array([margin, restoration, -spread])
    if not np.isfinite(features).all() or not np.isfinite(gain):
        raise ArithmeticError('Nonfinite cycle feature')
    return dict(gain=gain, margin=margin, renewal_spread=spread,
                restoration=restoration, identifiable=identifiable,
                features=features, numerator=numerator, denominator=denominator,
                signed=signed, unsigned=unsigned,
                per_probe_gain=np.sqrt(np.divide(numerator, denominator,
                    out=np.ones_like(numerator), where=denominator > 0)),
                renewal_displacement=np.sqrt(distance_squared(ao[:, 0], ai[:, 0])))


def scale_fit(x):
    x = np.asarray(x, float)
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError('Finite feature matrix required')
    mean, sd = x.mean(axis=0), x.std(axis=0)
    sd[sd <= 1e-12] = 1.
    return (x - mean) / sd, dict(mean=mean.tolist(), scale=sd.tolist())


def fit(x, y, ridge=.01, nonnegative=True):
    """Fit only on the caller's training rows; no feature or label selection."""
    y = np.asarray(y, float)
    z, scaling = scale_fit(x)
    if y.shape != (len(z),) or not np.isin(y, [0., 1.]).all() or not 0 < y.sum() < len(y):
        raise ValueError('Both binary classes required for a finite fitted intercept')
    a = np.c_[np.ones(len(z)), z]

    def objective(w):
        eta = a @ w
        loss = np.mean(np.logaddexp(0, eta) - y * eta) + .5 * ridge * (w[1:] @ w[1:])
        gradient = a.T @ (expit(eta) - y) / len(y)
        gradient[1:] += ridge * w[1:]
        return float(loss), gradient

    bounds = [(None, None)] + ([(0., None)] if nonnegative else [(None, None)]) * z.shape[1]
    result = minimize(objective, np.zeros(a.shape[1]), method='L-BFGS-B', jac=True,
                      bounds=bounds, options=dict(maxiter=2000, ftol=1e-14, gtol=1e-9))
    loss, gradient = objective(result.x)
    projected = gradient.copy()
    if nonnegative:
        at_bound = result.x[1:] <= 1e-10
        projected[1:][at_bound] = np.minimum(projected[1:][at_bound], 0.)
    residual = float(np.max(abs(projected)))
    if not result.success or residual > 1e-6:
        raise ArithmeticError(f'Fit not qualified: {result.message}; residual {residual}')
    return dict(type='logistic', scaling=scaling, coefficients=result.x.tolist(),
                ridge=ridge, nonnegative=nonnegative, loss=loss,
                projected_gradient=residual, iterations=int(result.nit))


def predict(x, fitted):
    state = fitted['scaling']
    z = (np.asarray(x, float) - state['mean']) / state['scale']
    return expit(np.c_[np.ones(len(z)), z] @ fitted['coefficients'])


def tt008_predict(initial_features):
    frozen = json.loads((ROOT / 'reference/tt008_FROZEN_MODELS.json').read_text())
    return predict(initial_features, frozen['candidate'])


def rival_channels(initial_features, incoming, outgoing, measured, windows, rule):
    aligned = windows.mean(axis=1) * rule * np.array([[1., -1.], [-1., 1.]])
    read_margins = aligned.min(axis=(-2, -1))
    diagnostics = np.concatenate([initial_features, measured['features'],
        measured['signed'].ravel(), measured['unsigned'].ravel(), read_margins.ravel(),
        measured['per_probe_gain'], measured['renewal_displacement'],
        [float(measured['identifiable'])]])
    full_operator = np.concatenate([operator(incoming[0, 0]).ravel(), operator(outgoing).ravel()])
    return diagnostics, full_operator
