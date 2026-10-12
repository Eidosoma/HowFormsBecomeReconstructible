"""Training-only preprocessing, blocked ridge selection and registered scoring."""
from __future__ import annotations
import numpy as np

ALPHAS = (.001, .01, .1, 1., 10., 100.)
BOOTSTRAP_SEED = 14120260917
BOOTSTRAP_DRAWS = 10000


def validate(x, groups, y=None):
    if x.ndim != 2 or x.shape[1] not in (4, 16) or not len(x) or not np.isfinite(x).all():
        raise ValueError('finite 4- or 16-feature matrix required')
    if groups.shape != (len(x),) or groups.dtype != np.int64 or not np.isin(groups, np.arange(4)).all():
        raise ValueError('four declared public groups required')
    if y is not None and (y.shape != (len(x),) or not np.isfinite(y).all() or np.any(abs(y) > 1)):
        raise ValueError('finite bounded outcomes required')


def fit(x, y, groups, alpha):
    validate(x, groups, y)
    if alpha not in ALPHAS or set(groups.tolist()) != set(range(4)):
        raise ValueError('declared alpha and all four training groups required')
    means = np.stack([x[groups == g].mean(axis=0) for g in range(4)])
    offsets = np.asarray([y[groups == g].mean() for g in range(4)])
    residual = x - means[groups]
    scales = np.sqrt(np.mean(residual**2, axis=0)); scales[scales <= 1e-12] = 1.
    z = residual / scales
    coefficients = np.linalg.solve(z.T @ z / len(x) + alpha * np.eye(x.shape[1]), z.T @ (y - offsets[groups]) / len(x))
    return dict(alpha=alpha, features=x.shape[1], group_feature_means=means.tolist(), group_outcome_means=offsets.tolist(),
                scales=scales.tolist(), coefficients=coefficients.tolist(), clip=[-1., 1.])


def predict(model, x, groups):
    validate(x, groups)
    if set(model) != {'alpha', 'features', 'group_feature_means', 'group_outcome_means', 'scales', 'coefficients', 'clip'}:
        raise ValueError('exact sealed model schema required')
    means, offsets, scales, beta = (np.asarray(model[k], dtype=np.float64) for k in
        ('group_feature_means', 'group_outcome_means', 'scales', 'coefficients'))
    if model['features'] != x.shape[1] or means.shape != (4, x.shape[1]) or offsets.shape != (4,) or scales.shape != (x.shape[1],) or beta.shape != scales.shape:
        raise ValueError('model/feature schema mismatch')
    if not all(np.isfinite(a).all() for a in (means, offsets, scales, beta)) or np.any(scales <= 0) or model['clip'] != [-1., 1.] or model['alpha'] not in ALPHAS:
        raise ValueError('invalid sealed model')
    return np.clip(offsets[groups] + ((x - means[groups]) / scales) @ beta, -1., 1.)


def select_and_fit(x, y, groups, blocks):
    validate(x, groups, y)
    if blocks.shape != (len(x),) or blocks.dtype != np.int64 or len(np.unique(blocks)) != 16:
        raise ValueError('sixteen complete founder blocks required')
    unique = np.unique(blocks)
    for block in unique:
        g = groups[blocks == block]
        if len(g) != 16 or any(np.sum(g == j) != 4 for j in range(4)):
            raise ValueError('retain all four lives and four cases per block')
    fold_predictions = np.zeros((len(ALPHAS), len(y)))
    fold_errors = np.zeros((len(ALPHAS), 16))
    for ai, alpha in enumerate(ALPHAS):
        for bi, block in enumerate(unique):
            test = blocks == block; train = ~test
            model = fit(x[train], y[train], groups[train], alpha)
            fold_predictions[ai, test] = predict(model, x[test], groups[test])
            fold_errors[ai, bi] = np.mean((fold_predictions[ai, test] - y[test])**2)
    losses = fold_errors.mean(axis=1)
    chosen = max(i for i in range(len(ALPHAS)) if losses[i] <= losses.min() + 1e-12)
    return dict(model=fit(x, y, groups, ALPHAS[chosen]), cv_alphas=list(ALPHAS),
        cv_block_mse=fold_errors.tolist(), cv_mse=losses.tolist(), selected_index=chosen,
        cv_predictions=fold_predictions[chosen].tolist(), blocks=unique.tolist(),
        prospective_evidence=False, preprocessing='training-only group centering and pooled residual SD')


def score(y, passive, challenge):
    """Synthetic/development usable; held-out outputs do not exist in this stage."""
    arrays = (y, passive, challenge)
    if any(a.shape != (16, 4, 4) or not np.isfinite(a).all() or np.any(abs(a) > 1) for a in arrays):
        raise ValueError('sixteen complete blocks of bounded outcomes/forecasts required')
    p = (passive - y)**2; c = (challenge - y)**2
    delta = (p-c).mean(axis=(1, 2))
    random = np.random.default_rng(BOOTSTRAP_SEED)
    sampled = delta[random.integers(0, 16, size=(BOOTSTRAP_DRAWS, 16))].mean(axis=1)
    lo, hi = np.quantile(sampled, (.025, .975))
    label = 'CHALLENGE_PREDICTIVE_GAIN' if lo > 0 else 'CHALLENGE_PREDICTIVE_HARM' if hi < 0 else 'PREDICTIVE_DIFFERENCE_UNRESOLVED'
    return dict(label=label, passive_mse=float(p.mean()), challenge_mse=float(c.mean()),
        mse_improvement=float(delta.mean()), ci95=[float(lo), float(hi)], block_differences=delta.tolist(),
        relative_reduction=float(delta.mean()/p.mean()) if p.mean() else None,
        passive_mae=float(np.mean(abs(passive-y))), challenge_mae=float(np.mean(abs(challenge-y))),
        independent_blocks=16, bootstrap_draws=BOOTSTRAP_DRAWS, bootstrap_seed=BOOTSTRAP_SEED)
