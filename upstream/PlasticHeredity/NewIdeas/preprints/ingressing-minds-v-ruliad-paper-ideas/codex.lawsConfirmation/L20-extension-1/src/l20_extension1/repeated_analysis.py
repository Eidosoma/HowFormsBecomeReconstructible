"""Frozen D142 variance characterization and descriptive fixed-forecast checks."""
import numpy as np
from . import diagnostics as dev

CASES = ((0, 'translated'), (0, 'aligned'), (1, 'translated'), (1, 'aligned'))
SEED, DRAWS = 14220260917, 10000


def components(y):
    y = np.asarray(y, dtype=float)
    if y.shape[-2:] != (64, 4) or not np.isfinite(y).all():
        raise ValueError('64 cases, four finite new futures required per group')
    means = y.mean(axis=-1)
    within = y.var(axis=-1, ddof=1).mean(axis=-1)
    between = means.var(axis=-1, ddof=1) - within/4
    total = within + between
    ratio = np.full_like(total, np.nan)
    np.divide(between, total, out=ratio, where=total > 0)
    return dict(within_future_variance=within, between_record_host_variance=between,
                total_variance=total, repeatability=ratio)


def group_statistics(y, draws):
    if y.shape != (16, 4, 4) or draws.shape != (DRAWS, 16):
        raise ValueError('sixteen whole blocks and registered bootstrap draws required')
    point = components(y.reshape(64, 4))
    boot = components(y[draws].reshape(DRAWS, 64, 4))
    rows = {}
    for k, value in point.items():
        undefined = int(np.count_nonzero(~np.isfinite(boot[k])))
        rows[k] = dict(estimate=float(value) if np.isfinite(value) else None,
            pointwise_block_bootstrap_95=None if undefined else np.quantile(boot[k], [.025, .975]).tolist(),
            undefined_bootstrap_draws=undefined)
    return rows


def fixed_forecasts(y, predictions):
    if y.shape != (64, 4) or predictions.shape != (64,) or not np.isfinite(y).all() or not np.isfinite(predictions).all():
        raise ValueError('all new futures and fixed finite forecasts required')
    w = float(y.var(axis=1, ddof=1).mean())
    mse_mean = float(np.mean((predictions-y.mean(axis=1))**2))
    mse = float(np.mean((predictions[:, None]-y)**2))
    corrected = mse_mean-w/4
    assert abs(mse - (corrected+w)) < 1e-12
    return dict(fresh_future_mse=mse, fresh_future_mae=float(np.mean(abs(predictions[:, None]-y))),
        four_future_mean_mse=mse_mean, noise_corrected_mean_target_mse=corrected,
        estimated_noise_variance=w, identity_residual=mse-(corrected+w))


def correlation(a, b):
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def fidelity(block):
    # block axes: life, future, condition, generation, byte.
    incoming = block['incoming'][..., 0, :]
    packets = np.concatenate((incoming[..., None, :], block['outgoing']), axis=-2)
    fields = np.ascontiguousarray(packets).view('<f8').reshape(4, 4, 4, 4, 16, 16)
    centered = fields - fields.mean(axis=(-2, -1), keepdims=True)
    scale = fields.std(axis=(-2, -1))
    result = np.zeros((4, 4, 4, 4))
    for ci, (role, _) in enumerate(CASES):
        scores = np.einsum('sij,...ij->...s', dev.template_bank()[role], centered[:, :, ci], optimize=False)
        np.divide(scores.max(axis=-1), 256*scale[:, :, ci], out=result[:, :, ci], where=scale[:, :, ci] > 0)
    return result


def summarize(blocks, metadata, predictions, original):
    if len(blocks) != 16 or len(metadata) != 16 or predictions.shape != (16, 4, 4, 3) or original.shape != (16, 4, 4):
        raise ValueError('complete balanced blocks, three fixed forecasts and separate old outcomes required')
    y = np.stack([b['terminal_values'][..., -1, 0] - b['terminal_values'][..., -1, 1] for b in blocks])
    assert y.shape == (16, 4, 4, 4) and np.isfinite(y).all()
    gen = np.stack([b['values'][..., -1, 0] - b['values'][..., -1, 1] for b in blocks])
    trajectory = np.concatenate((gen, y[..., None]), axis=-1)
    shapes = np.stack([fidelity(b) for b in blocks])
    labels = np.array([[[[[p['selector']['inferred_family'] for p in entry['paths'][ci]['generations']] +
        [entry['paths'][ci]['terminal']['selector']['inferred_family']] for ci in range(4)]
        for entry in life] for life in m['lives']] for m in metadata], dtype=object)
    draws = np.random.default_rng(SEED).integers(0, 16, (DRAWS, 16))
    groups = {}
    for ci, (role, writer) in enumerate(CASES):
        group_y = y[..., ci]
        flat = group_y.reshape(64, 4)
        negatives = (flat < 0).sum(axis=1)
        old = original[..., ci].reshape(64)
        cross = [[int(np.sum(((old < 0) if was_negative else (old >= 0)) & (negatives == n)))
                  for n in range(5)] for was_negative in (False, True)]
        group = dict(primary=group_statistics(group_y, draws),
            case_means=flat.mean(axis=1).tolist(), case_sample_variances=flat.var(axis=1, ddof=1).tolist(),
            new_future_values=flat.tolist(), negative_futures_per_case_histogram=np.bincount(negatives, minlength=5).tolist(),
            zero_outcomes=int(np.sum(flat == 0)), original_negative_by_new_negative_count=cross,
            original_to_new_mean_correlation=correlation(old, flat.mean(axis=1)),
            mean_preference_G1_G4=trajectory[..., ci, :].mean(axis=(0, 1, 2)).tolist(),
            negative_preference_G1_G4=(trajectory[..., ci, :] < 0).sum(axis=(0, 1, 2)).tolist(),
            non_own_guide_G1_G4=(labels[..., ci, :] != role).sum(axis=(0, 1, 2)).tolist(),
            mean_record_best_F0_F3=shapes[..., ci, :].mean(axis=(0, 1, 2)).tolist(),
            fixed_predictors={name: fixed_forecasts(flat, predictions[..., ci, mi].reshape(64))
                for mi, name in enumerate(('starting_only', 'passive', 'challenge'))})
        groups[f'{"AB"[role]}_{writer}'] = group
    return dict(schema='d142_repeated_futures_variance_v1', stage='FIXED_COHORT_FRESH_FUTURES',
        blocks=list(range(90000, 90016)), independent_blocks=16, lives_per_block=4, futures_per_case=4,
        cases=256, terminal_outcomes=1024, new_founders=0, refitted_models=0,
        bootstrap_seed=SEED, bootstrap_draws=DRAWS, groups=groups,
        original_outcomes_enter_primary=False, variance_estimates_clipped=False,
        multiplicity_adjusted=False, automatic_successor=False,
        interpretation='Conditional on existing record-host pairs, fixed guide/rules and four new noise streams; not a new founder cohort or a revised challenge contest.')
