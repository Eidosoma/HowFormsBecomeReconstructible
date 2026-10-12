"""Independent D142 sums-of-squares, block uncertainty and FFT shape checks."""
import numpy as np
from .repeated_audit import physics


def moments(y):
    n, r = y.shape[-2:]
    assert (n, r) == (64, 4)
    m = np.add.reduce(y, axis=-1) / r
    # Pairwise differences restate the within-case unbiased variance.
    w = sum(np.add.reduce((y[..., a]-y[..., b])**2, axis=-1) for a in range(r) for b in range(a+1, r)) / (n*r*(r-1))
    center = np.add.reduce(m, axis=-1) / n
    b = np.add.reduce((m-center[..., None])**2, axis=-1)/(n-1) - w/r
    total = b+w
    ratio = np.full_like(total, np.nan)
    np.divide(b, total, out=ratio, where=total > 0)
    return dict(within_future_variance=w, between_record_host_variance=b, total_variance=total, repeatability=ratio)


def check(summary, blocks, metadata, forecasts, original):
    assert len(blocks) == len(metadata) == 16
    assert forecasts.shape == (16, 4, 4, 3) and original.shape == (16, 4, 4)
    y = np.stack([np.subtract(b['terminal_values'][..., -1, 0], b['terminal_values'][..., -1, 1]) for b in blocks])
    draws = np.random.default_rng(14220260917).integers(0, 16, (10000, 16))
    yy, xx = np.indices((16, 16))
    targets = (np.where(yy < 8, 1., -1.), np.where(xx % 8 < 4, 1., -1.))
    worst = 0.
    for ci, name in enumerate(('A_translated', 'A_aligned', 'B_translated', 'B_aligned')):
        g = summary['groups'][name]; role = ci//2
        panel = y[..., ci]; flat = panel.reshape(64, 4)
        m, boots = moments(flat), moments(panel[draws].reshape(10000, 64, 4))
        expected = {}
        for k in m:
            invalid = int(np.sum(~np.isfinite(boots[k])))
            expected[k] = dict(estimate=float(m[k]) if np.isfinite(m[k]) else None,
                pointwise_block_bootstrap_95=None if invalid else np.percentile(boots[k], [2.5, 97.5]).tolist(),
                undefined_bootstrap_draws=invalid)
        physics.nested(g['primary'], expected)
        means = np.add.reduce(flat, axis=1)/4
        variance = np.add.reduce((flat-means[:, None])**2, axis=1)/3
        physics.nested(g['case_means'], means.tolist()); physics.nested(g['case_sample_variances'], variance.tolist())
        physics.nested(g['new_future_values'], flat.tolist())
        negative = [sum(value < 0 for value in row) for row in flat]
        assert g['negative_futures_per_case_histogram'] == [negative.count(n) for n in range(5)]
        assert g['zero_outcomes'] == int((flat == 0).sum())
        old = original[..., ci].reshape(64)
        assert g['original_negative_by_new_negative_count'] == [[sum((o < 0) == flag and n == k for o, n in zip(old, negative))
            for k in range(5)] for flag in (False, True)]
        centered_old, centered_mean = old-old.mean(), means-means.mean()
        den = float(np.linalg.norm(centered_old)*np.linalg.norm(centered_mean))
        corr = float(centered_old@centered_mean/den) if den else None
        physics.nested(g['original_to_new_mean_correlation'], corr)
        gen = np.stack([b['values'][:, :, ci, :, -1, 0]-b['values'][:, :, ci, :, -1, 1] for b in blocks])
        trace = np.concatenate((gen, panel[..., None]), axis=-1)
        physics.nested(g['mean_preference_G1_G4'], (trace.sum(axis=(0, 1, 2))/256).tolist())
        assert g['negative_preference_G1_G4'] == (trace < 0).sum(axis=(0, 1, 2)).tolist()
        guide_counts = [0]*4; shape_sums = np.zeros(4)
        for bi, block in enumerate(blocks):
            for life in range(4):
                for future in range(4):
                    path = metadata[bi]['lives'][life][future]['paths'][ci]
                    choices = [r['selector']['inferred_family'] for r in path['generations']] + [path['terminal']['selector']['inferred_family']]
                    for stage, choice in enumerate(choices): guide_counts[stage] += int(choice != role)
                    packets = [block['incoming'][life, future, ci, 0]] + list(block['outgoing'][life, future, ci])
                    for stage, packet in enumerate(packets):
                        field = np.frombuffer(packet.tobytes(), '<f8').reshape(16, 16)
                        sd = field.std()
                        value = np.fft.ifft2(np.fft.fft2(field-field.mean())*np.conjugate(np.fft.fft2(targets[role]))).real.max()/(256*sd) if sd else 0.
                        shape_sums[stage] += value
        assert guide_counts == g['non_own_guide_G1_G4']
        error = float(np.max(abs(shape_sums/256 - g['mean_record_best_F0_F3'])))
        assert error < 1e-12; worst = max(worst, error)
        for mi, model in enumerate(('starting_only', 'passive', 'challenge')):
            predictions = forecasts[..., ci, mi].reshape(64)
            residuals = predictions[:, None]-flat
            mse = float(np.sum(residuals**2)/256)
            mean_mse = float(np.sum((predictions-means)**2)/64)
            correction = mean_mse-float(m['within_future_variance'])/4
            wanted = dict(fresh_future_mse=mse, fresh_future_mae=float(np.sum(abs(residuals))/256),
                four_future_mean_mse=mean_mse, noise_corrected_mean_target_mse=correction,
                estimated_noise_variance=float(m['within_future_variance']), identity_residual=mse-(correction+float(m['within_future_variance'])))
            physics.nested(g['fixed_predictors'][model], wanted)
    expected_top = dict(schema='d142_repeated_futures_variance_v1', stage='FIXED_COHORT_FRESH_FUTURES',
        blocks=list(range(90000, 90016)), independent_blocks=16, lives_per_block=4, futures_per_case=4,
        cases=256, terminal_outcomes=1024, new_founders=0, refitted_models=0,
        bootstrap_seed=14220260917, bootstrap_draws=10000,
        original_outcomes_enter_primary=False, variance_estimates_clipped=False,
        multiplicity_adjusted=False, automatic_successor=False,
        interpretation='Conditional on existing record-host pairs, fixed guide/rules and four new noise streams; not a new founder cohort or a revised challenge contest.')
    physics.nested({k: v for k, v in summary.items() if k != 'groups'}, expected_top)
    assert set(summary['groups']) == {'A_translated', 'A_aligned', 'B_translated', 'B_aligned'}
    return dict(passes=True, independent_blocks=16, cases=256, fresh_terminal_outcomes=1024,
        fft_shape_checks=4096, max_shape_error=worst, new_dynamics=0)
