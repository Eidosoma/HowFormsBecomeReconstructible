"""D171 independent group-coordinate SVD and saved-score checker.

Does not call production fitting, embedding, preprocessing or reporting code.
Constants/schema are shared; numerical results are rebuilt here.
"""
import numpy as np
from . import settings_prediction as spec

ATOL = 2e-10
H = np.array([[-.5, -.5, .5], [-.5, .5, -.5], [.5, -.5, -.5], [.5, .5, .5]])


def same(actual, expected):
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), 'mapping schema'
        for key in expected:
            same(actual[key], expected[key])
    elif isinstance(expected, (list, tuple, np.ndarray)):
        try:
            e, a = np.asarray(expected, dtype=float), np.asarray(actual, dtype=float)
        except (ValueError, TypeError):
            assert isinstance(actual, (list, tuple)) and len(actual) == len(expected)
            for a, e in zip(actual, expected):
                same(a, e)
        else:
            assert a.shape == e.shape and np.isfinite(a).all() and np.isfinite(e).all()
            np.testing.assert_allclose(a, e, atol=ATOL, rtol=0)
    elif isinstance(expected, (float, np.floating)):
        assert np.isfinite(actual) and abs(actual - expected) <= ATOL
    else:
        assert actual == expected, (actual, expected)


def rolled_q(shifts):
    a = np.ones((16, 16)); a[8:] = -1
    b = np.ones((16, 16)); b[:, np.arange(16) % 8 >= 4] = -1
    result = np.ones(shifts.shape[:-1])
    for i, life, group, slot in np.ndindex(result.shape):
        if group % 2 == 0:
            shape = (a, b)[group // 2]
            dy, dx = shifts[i, life, group, slot]
            result[i, life, group, slot] = np.mean(shape * np.roll(shape, (int(dy), int(dx)), axis=(0, 1)))
    return result


def features(data, settings):
    a, e, t = (data[k] for k in ('start', 'endpoint', 'targeted'))
    result = {'starting': a, 'one_copy': np.concatenate((a, e[..., 0, :]), axis=-1)}
    seconds = (e[..., 1, :], e[..., 2, :], t[..., 0, :], t[..., 1, :], t[..., 2, :])
    for name, second in zip(spec.OBSERVERS[2:], seconds):
        result[name] = np.concatenate((a, e[..., 0, :], second), axis=-1)
    if settings:
        q = rolled_q(data['shifts'])
        result = {k: np.concatenate((v, q), axis=-1) for k, v in result.items()}
    return result


def frame(x, y, g, tied):
    d = x.shape[1]
    mu = np.stack([np.sum(x[g == j], axis=0) / np.sum(g == j) for j in range(4)])
    offset = np.array([np.sum(y[g == j]) / np.sum(g == j) for j in range(4)])
    centered = x - mu[g]
    s = np.sqrt(np.sum(centered ** 2, axis=0) / len(x)); s[s <= 1e-12] = 1
    transform = np.eye(d)
    if tied:
        transform = np.zeros((d, d - 6)); transform[:7, :7] = np.eye(7)
        for j in range(6):
            h = np.sqrt(s[7 + j] ** 2 + s[13 + j] ** 2)
            transform[7 + j, 7 + j] = s[7 + j] / h
            transform[13 + j, 7 + j] = s[13 + j] / h
        if d == 21:
            transform[19, 13] = 1; transform[20, 14] = 1
    return mu, offset, s, transform, centered / s, y - offset[g]


def svd_solution(x, y, g, test, h, alpha, tied):
    mu, offset, s, transform, z, target = frame(x, y, g, tied)
    reduced = z @ transform
    # P=I-(3/16)11'; P^(-1/2)=I+(1/4)11' in four actual-group slopes.
    white = np.eye(4) + .25 * np.ones((4, 4))
    design = np.einsum('ig,ij->igj', white[g], reduced).reshape(len(y), -1)
    u, singular, vh = np.linalg.svd(design / np.sqrt(len(y)), full_matrices=False)
    theta = (vh.T @ ((singular / (singular ** 2 + alpha)) * (u.T @ (target / np.sqrt(len(y)))))).reshape(4, -1)
    group_slopes = white @ theta
    eta = np.vstack((group_slopes.mean(0), H.T @ group_slopes))
    beta = eta @ transform.T
    raw = offset[h] + np.sum((((test - mu[h]) / s) @ transform) * group_slopes[h], axis=1)
    return dict(means=mu, offsets=offset, scale=s, coefficients=beta, reduced_coefficients=eta), raw


def verify_model(record, x, y, g, test, h, raw, alpha, tied, settings):
    mu, offset, s, transform, z, target = frame(x, y, g, tied)
    assert record['alpha'] == alpha
    assert record['model_class'] == (spec.NEW_CLASSES if settings else spec.OLD_CLASSES)[int(tied)]
    for key, val in (('means', mu), ('offsets', offset), ('scale', s)):
        same(record[key], val)
    beta = np.asarray(record['coefficients']); assert beta.shape == (4, len(s)) and np.isfinite(beta).all()
    eta = beta @ transform
    same(eta @ transform.T, beta)
    if 'reduced_coefficients' in record:
        same(record['reduced_coefficients'], eta)
    same(transform.T @ transform, np.eye(transform.shape[1]))
    actual_slopes = beta[0] + H @ beta[1:]
    expected_raw = offset[h] + np.sum(((test - mu[h]) / s) * actual_slopes[h], axis=1)
    same(raw, expected_raw)
    reduced = z @ transform
    design = np.hstack([reduced] + [reduced * H[g, j, None] for j in range(3)])
    grad = design.T @ (design @ eta.ravel() - target) / len(y) + alpha * eta.ravel()
    same(grad, np.zeros_like(grad))
    tie_error = 0.
    if tied:
        delta = beta[:, 7:13] / s[7:13] - beta[:, 13:19] / s[13:19]
        same(delta, np.zeros_like(delta)); tie_error = float(abs(delta).max())
    svd_error = 0.
    if settings:
        expected, p = svd_solution(x, y, g, test, h, alpha, tied)
        for key, val in expected.items():
            same(record[key], val)
        same(raw, p); svd_error = float(np.max(abs(raw - p)))
    objective = float(np.mean((design @ eta.ravel() - target) ** 2) + alpha * np.sum(beta ** 2))
    return objective, float(np.max(abs(grad))), tie_error, svd_error


def verify_fits(data, new, new_raw, fits, old, old_raw, references):
    n = spec.validate(data); ids = data['block_ids']; y = data['futures'].mean(-1).ravel()
    g = np.tile(np.arange(4, dtype=np.int64), n * 4); rows = np.repeat(np.arange(n), 16)
    xnew, xold = features(data, True), features(data, False)
    same(spec.effective_q(data['shifts']), rolled_q(data['shifts']))
    production = spec.panels({k: data[k] for k in spec.MEASUREMENTS})
    same(production, xnew)
    for container in (new, new_raw, fits, old, old_raw, references):
        assert set(container) == set(spec.OBSERVERS)
    maxima = np.zeros(3); nesting_max = -float('inf'); checked = 0
    for name in spec.OBSERVERS:
        tied = name.startswith('tied:')
        for p, raw in ((new[name], new_raw[name]), (old[name], old_raw[name])):
            assert p.shape == raw.shape == (3, n, 4, 4)
            assert np.isfinite(raw).all(); np.testing.assert_array_equal(p, np.clip(raw, -1, 1))
        for records in (fits[name], references[name]):
            assert records['observer'] == name and records['blocks'] == ids.tolist()
            assert records['alphas'] == list(spec.ALPHAS) and records['target'] == 'future_mean'
            assert len(records['folds']) == n
        xn = xnew[name].reshape(n * 16, -1); xo = xold[name].reshape(n * 16, -1)
        np.testing.assert_array_equal(xn[:, :-2], xo)
        for outer in range(n):
            train, test = rows != outer, rows == outer
            nf, of = fits[name]['folds'][outer], references[name]['folds'][outer]
            for fold in (nf, of):
                assert fold['validation_block'] == int(ids[outer])
                assert fold['training_blocks'] == ids[np.arange(n) != outer].tolist()
                assert len(fold['models']) == 3
            for i, alpha in enumerate(spec.ALPHAS):
                nm, om = nf['models'][i], of['models'][i]
                args = (y[train], g[train])
                no, ng, nt, ns = verify_model(nm, xn[train], *args, xn[test], g[test], new_raw[name][i, outer].ravel(), alpha, tied, True)
                oo, og, ot, _ = verify_model(om, xo[train], *args, xo[test], g[test], old_raw[name][i, outer].ravel(), alpha, tied, False)
                same(np.asarray(nm['means'])[:, :-2], om['means']); same(nm['scale'][:-2], om['scale'])
                same(nm['offsets'], om['offsets'])
                # Zero-extend the old coefficients in the *original* objective.
                extended = np.pad(np.asarray(om['coefficients']), ((0, 0), (0, 2)))
                mu, offset, s, transform, z, target = frame(xn[train], *args, tied)
                same(extended @ transform @ transform.T, extended)
                slopes = extended[0] + H @ extended[1:]
                nested = float(np.mean((np.sum(z * slopes[g[train]], axis=1) - target) ** 2)
                               + alpha * np.sum(extended ** 2))
                same(nested, oo); assert no <= oo + ATOL, 'nested optimum cannot worsen unclipped training objective'
                nesting_max = max(nesting_max, no - oo)
                maxima = np.maximum(maxima, (max(ng, og), max(nt, ot), ns)); checked += 1
    return dict(passes=True, new_svd_solutions_checked=checked, saved_reference_optima_checked=checked,
                statistical_predictions=checked * 16, actual_reference_refits=0,
                max_stationarity=float(maxima[0]), max_raw_tie_error=float(maxima[1]),
                max_svd_prediction_error=float(maxima[2]), max_training_objective_change=nesting_max,
                all_whole_founder_exclusions_checked=True, zero_settings_nesting_checked=True)


def metric_check(saved, p, raw, f):
    error = p[:, :, :, None] - f; sq = np.square(error); n = len(p)
    bm = [float(np.average(sq[i])) for i in range(n)]
    gm = [float(np.average(sq[:, :, j, :])) for j in range(4)]
    expected = dict(mse=float(np.average(bm)), mae_points=float(100 * np.average(np.abs(error))),
        rmse_points=float(100 * np.sqrt(np.average(bm))), bias_points=float(100 * np.average(error)),
        clipped=int(np.sum(np.abs(raw) > 1)), cases=n * 16, block_mse=bm, group_mse=gm,
        block_mae_points=[float(100 * np.mean(abs(error[i]))) for i in range(n)],
        group_mae_points=[float(100 * np.mean(abs(error[:, :, j]))) for j in range(4)],
        block_bias_points=[float(100 * np.mean(error[i])) for i in range(n)],
        group_bias_points=[float(100 * np.mean(error[:, :, j])) for j in range(4)],
        group_clipped=[int(np.sum(abs(raw[:, :, j]) > 1)) for j in range(4)],
        future_mse=[float(np.mean(sq[..., j])) for j in range(4)],
        mean_target_mse=float(np.mean(np.square(p - f.sum(-1) / 4))),
        block_mean_target_mse=[float(np.mean((p[i] - f[i].sum(-1) / 4) ** 2)) for i in range(n)],
        irreducible_future_variance=float(np.mean((f - f.mean(-1)[..., None]) ** 2)))
    same(saved, expected)
    same(saved['mse'], saved['mean_target_mse'] + saved['irreducible_future_variance'])


def gain_check(saved, gain, extra):
    n = len(gain); b = np.array([gain[i].sum() / 16 for i in range(n)])
    expected = dict(extra, mse_reduction=float(np.average(b)), block_gains=b.tolist(),
        group_gains=[float(gain[:, :, j].mean()) for j in range(4)],
        positive_blocks=int(sum(v > 0 for v in b)), negative_blocks=int(sum(v < 0 for v in b)),
        zero_blocks=int(sum(v == 0 for v in b)),
        score_only_omit_gains=[float(np.delete(b, i).mean()) for i in range(n)])
    same(saved, expected)


def verify_report(summary, losses, data, new, new_raw, old, old_raw):
    f = data['futures']; n = len(f)
    values = {'old': old, 'settings': new}; raws = {'old': old_raw, 'settings': new_raw}
    expected_meta = dict(schema='d171_settings_prediction_development_v1', blocks=data['block_ids'].tolist(),
        cases=n * 16, new_fits=21 * n, new_predictions=336 * n,
        focal=dict(candidate='tied:sham_minus', reference='tied:passive', alpha=.01),
        prospective_evidence=False, new_dynamics=0, new_founders=0, new_lineages=0,
        actual_reference_refits=0, confidence_intervals=False, deployment_selection=False,
        automatic_successor=False, all_cases_retained=True, settings_equal_for_all_observers=True)
    panels = {'absolute', 'comparisons', 'gap_changes', 'cheap_selection_context', 'selected_cheap_comparisons'}
    same({k: v for k, v in summary.items() if k not in panels}, expected_meta)
    keys = {v + '/' + k for v in ('old', 'settings') for k in spec.OBSERVERS}
    assert set(summary['absolute']) == set(losses) == keys
    expected_losses, mean_losses = {}, {}
    for v in ('old', 'settings'):
        for k in spec.OBSERVERS:
            key = v + '/' + k; p = values[v][k]
            expected_losses[key] = np.sum((p[..., None] - f) ** 2, axis=-1) / 4
            mean_losses[key] = (p - f.sum(-1) / 4) ** 2
            same(losses[key], expected_losses[key])
            assert len(summary['absolute'][key]) == 3
            for i in range(3):
                metric_check(summary['absolute'][key][i], p[i], raws[v][k][i], f)
    pair_list = [('settings/' + k, 'old/' + k) for k in spec.OBSERVERS]
    pair_list.extend((v + '/' + k, v + '/tied:passive') for v in ('old', 'settings') for k in spec.OBSERVERS[3:])
    pair_list.extend((v + '/' + k, w + '/' + cheap) for v in ('old', 'settings')
                     for k in ('tied:passive', 'tied:sham_minus') for w in ('old', 'settings') for cheap in ('starting', 'one_copy'))
    assert len(pair_list) == 31 and len(summary['comparisons']) == 93
    pos = 0
    for c, r in pair_list:
        for i, a in enumerate((.001, .01, .1)):
            gain = expected_losses[r][i] - expected_losses[c][i]
            np.testing.assert_allclose(gain, mean_losses[r][i] - mean_losses[c][i], atol=1e-14, rtol=0)
            gain_check(summary['comparisons'][pos], gain, dict(candidate=c, reference=r, alpha=a)); pos += 1
    assert len(summary['gap_changes']) == 12; pos = 0
    for k in spec.OBSERVERS[3:]:
        for i, a in enumerate((.001, .01, .1)):
            change = (expected_losses['settings/tied:passive'][i] - expected_losses['settings/' + k][i]
                      - expected_losses['old/tied:passive'][i] + expected_losses['old/' + k][i])
            gain_check(summary['gap_changes'][pos], change, dict(challenge=k, alpha=a)); pos += 1
    choices = summary['cheap_selection_context']; cheap_keys = {v + '/' + k for v in ('old', 'settings') for k in ('starting', 'one_copy')}
    assert set(choices) == cheap_keys
    for key in cheap_keys:
        errors = expected_losses[key].mean((1, 2, 3)); best = max(i for i in range(3) if errors[i] <= min(errors) + 1e-12)
        same(choices[key], dict(index=best, alpha=(.001, .01, .1)[best], metrics=summary['absolute'][key][best], selection_affected=True))
    assert len(summary['selected_cheap_comparisons']) == 16; pos = 0
    for v in ('old', 'settings'):
        for k in ('tied:passive', 'tied:sham_minus'):
            for w in ('old', 'settings'):
                for cheap in ('starting', 'one_copy'):
                    c, r = v + '/' + k, w + '/' + cheap; choice = choices[r]
                    gain_check(summary['selected_cheap_comparisons'][pos], expected_losses[r][choice['index']] - expected_losses[c][1],
                        dict(candidate=c, candidate_alpha=.01, reference=r, reference_alpha=choice['alpha'], selection_affected=True))
                    pos += 1
    return dict(passes=True, absolute_score_records=42, paired_comparisons=93, gap_changes=12,
                cheap_selected_context_records=16, mean_future_gain_identity=True,
                all_founders_groups_futures_retained=True, intervals_computed=False)
